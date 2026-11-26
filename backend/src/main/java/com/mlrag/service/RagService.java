package com.mlrag.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mlrag.dto.ChatResponse;
import com.mlrag.dto.ChunkDto;
import com.mlrag.entity.ChatLog;
import com.mlrag.entity.DocumentItem;
import com.mlrag.entity.User;
import com.mlrag.repository.ChatLogRepository;
import com.mlrag.repository.DocumentItemRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class RagService {

    private final RestClient restClient;
    private final ChatLogRepository chatLogRepository;
    private final DocumentItemRepository documentItemRepository;
    private final ObjectMapper objectMapper;

    public RagService(
            @Value("${app.rag.service-url:http://127.0.0.1:8000}") String ragServiceUrl,
            ChatLogRepository chatLogRepository,
            DocumentItemRepository documentItemRepository,
            ObjectMapper objectMapper,
            RestClient.Builder restClientBuilder
    ) {
        this.restClient = restClientBuilder.baseUrl(ragServiceUrl).build();
        this.chatLogRepository = chatLogRepository;
        this.documentItemRepository = documentItemRepository;
        this.objectMapper = objectMapper;
    }

    public ChatResponse askQuestion(String question, User user) {
        try {
            String userId = user != null ? user.getUsername() : "default";
            String jsonPayload = objectMapper.writeValueAsString(Map.of(
                    "question", question,
                    "user_id", userId
            ));

            String responseString = restClient.post()
                    .uri("/api/rag/ask")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(jsonPayload)
                    .retrieve()
                    .body(String.class);

            JsonNode root = objectMapper.readTree(responseString);
            String answer = root.path("answer").asText("");

            List<ChunkDto> chunks = new ArrayList<>();
            JsonNode chunksNode = root.path("chunks");
            if (chunksNode.isArray()) {
                int idx = 1;
                for (JsonNode c : chunksNode) {
                    ChunkDto chunk = new ChunkDto();
                    chunk.setId(idx++);
                    chunk.setChunkId(c.path("chunk_id").asInt());
                    chunk.setPage(c.path("page").asInt(1));
                    chunk.setStartChar(c.path("start_char").asInt(0));
                    chunk.setEndChar(c.path("end_char").asInt(0));
                    chunk.setSource(c.path("source").asText("document"));
                    chunk.setText(c.path("text").asText(""));
                    chunk.setDistance(c.path("distance").asDouble(0.0));
                    chunk.setChunkType(c.path("chunk_type").asText("body"));
                    chunk.setTableId(c.path("table_id").asInt(0));
                    chunks.add(chunk);
                }
            }

            // Save to MySQL ChatLog
            ChatLog log = new ChatLog(
                    user != null ? user.getId() : null,
                    user != null ? user.getUsername() : "anonymous",
                    question,
                    answer,
                    chunks.size()
            );
            chatLogRepository.save(log);

            return new ChatResponse(question, answer, chunks);
        } catch (Exception e) {
            String fallbackAnswer = "Unable to reach RAG AI Engine (" + e.getMessage() + "). Please ensure the RAG service is running on port 8000.";
            return new ChatResponse(question, fallbackAnswer, List.of());
        }
    }

    public DocumentItem uploadAndIndex(String originalFilename, byte[] bytes, User user) {
        int chunkCount = 0;
        String userId = user != null ? user.getUsername() : "default";
        try {
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            ByteArrayResource resource = new ByteArrayResource(bytes) {
                @Override
                public String getFilename() {
                    return originalFilename;
                }
            };
            body.add("file", resource);
            body.add("user_id", userId);

            String responseString = restClient.post()
                    .uri("/api/rag/upload")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .body(String.class);

            JsonNode root = objectMapper.readTree(responseString);
            chunkCount = root.path("chunk_count").asInt(0);
        } catch (Exception e) {
            // Log warning, will still record metadata
        }

        String extension = "";
        if (originalFilename.contains(".")) {
            extension = originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase();
        }

        DocumentItem doc = new DocumentItem(
                originalFilename,
                extension,
                (long) bytes.length,
                chunkCount,
                user != null ? user.getUsername() : "system"
        );
        return documentItemRepository.save(doc);
    }

    public List<ChunkDto> getAllIndexedChunks(User user) {
        if (user == null) {
            return List.of();
        }
        try {
            String userId = user.getUsername();
            String responseString = restClient.get()
                    .uri(uriBuilder -> uriBuilder.path("/api/rag/chunks").queryParam("user_id", userId).build())
                    .retrieve()
                    .body(String.class);

            JsonNode root = objectMapper.readTree(responseString);
            List<ChunkDto> chunks = new ArrayList<>();
            if (root.isArray()) {
                int idx = 1;
                for (JsonNode c : root) {
                    ChunkDto chunk = new ChunkDto();
                    chunk.setId(idx++);
                    chunk.setChunkId(c.path("chunk_id").asInt());
                    chunk.setPage(c.path("page").asInt(1));
                    chunk.setStartChar(c.path("start_char").asInt(0));
                    chunk.setEndChar(c.path("end_char").asInt(0));
                    chunk.setSource(c.path("source").asText(""));
                    chunk.setText(c.path("text").asText(""));
                    chunk.setDistance(c.path("distance").asDouble(0.0));
                    chunk.setChunkType(c.path("chunk_type").asText("body"));
                    chunk.setTableId(c.path("table_id").asInt(0));
                    chunks.add(chunk);
                }
            }
            return chunks;
        } catch (Exception e) {
            return List.of();
        }
    }

    public List<ChatLog> getUserChatLogs(Long userId) {
        return chatLogRepository.findByUserIdOrderByTimestampDesc(userId);
    }

    public List<ChatLog> getAllChatLogs() {
        return chatLogRepository.findAllByOrderByTimestampDesc();
    }

    public boolean deleteChatLog(Long id, User user) {
        return chatLogRepository.findById(id).map(log -> {
            if (user == null || log.getUserId() == null || log.getUserId().equals(user.getId()) || "ROLE_ADMIN".equals(user.getRole())) {
                chatLogRepository.delete(log);
                return true;
            }
            return false;
        }).orElse(false);
    }

    public void clearChatLogs(User user) {
        if (user != null) {
            if ("ROLE_ADMIN".equals(user.getRole())) {
                chatLogRepository.deleteAll();
            } else {
                List<ChatLog> userLogs = chatLogRepository.findByUserIdOrderByTimestampDesc(user.getId());
                chatLogRepository.deleteAll(userLogs);
            }
        }
    }

    public List<DocumentItem> getDocuments(User user) {
        if (user == null) {
            return List.of();
        }
        if ("ROLE_ADMIN".equals(user.getRole())) {
            return documentItemRepository.findAllByOrderByUploadedAtDesc();
        }
        return documentItemRepository.findByUploadedByOrderByUploadedAtDesc(user.getUsername());
    }

    public String getDocumentStructure(User user) {
        if (user == null) {
            return "[]";
        }
        try {
            String userId = user.getUsername();
            return restClient.get()
                    .uri(uriBuilder -> uriBuilder.path("/api/rag/structure").queryParam("user_id", userId).build())
                    .retrieve()
                    .body(String.class);
        } catch (Exception e) {
            return "[]";
        }
    }

    public String getDocumentTables(User user) {
        if (user == null) {
            return "[]";
        }
        try {
            String userId = user.getUsername();
            return restClient.get()
                    .uri(uriBuilder -> uriBuilder.path("/api/rag/tables").queryParam("user_id", userId).build())
                    .retrieve()
                    .body(String.class);
        } catch (Exception e) {
            return "[]";
        }
    }
}

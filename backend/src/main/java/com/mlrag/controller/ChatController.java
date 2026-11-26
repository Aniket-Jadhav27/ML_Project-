package com.mlrag.controller;

import com.mlrag.dto.ChatRequest;
import com.mlrag.dto.ChatResponse;
import com.mlrag.entity.ChatLog;
import com.mlrag.entity.User;
import com.mlrag.service.RagService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final RagService ragService;

    public ChatController(RagService ragService) {
        this.ragService = ragService;
    }

    @PostMapping("/ask")
    public ResponseEntity<?> ask(
            @Valid @RequestBody ChatRequest request,
            @AuthenticationPrincipal User user
    ) {
        if (request.getQuestion() == null || request.getQuestion().trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("message", "Question cannot be empty"));
        }
        ChatResponse response = ragService.askQuestion(request.getQuestion().trim(), user);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/history")
    public ResponseEntity<List<ChatLog>> getHistory(@AuthenticationPrincipal User user) {
        if (user != null) {
            if ("ROLE_ADMIN".equals(user.getRole())) {
                return ResponseEntity.ok(ragService.getAllChatLogs());
            }
            return ResponseEntity.ok(ragService.getUserChatLogs(user.getId()));
        }
        return ResponseEntity.ok(List.of());
    }

    @DeleteMapping("/history/{id}")
    public ResponseEntity<?> deleteHistoryItem(@PathVariable Long id, @AuthenticationPrincipal User user) {
        boolean deleted = ragService.deleteChatLog(id, user);
        if (deleted) {
            return ResponseEntity.ok(Map.of("message", "Chat log deleted successfully"));
        }
        return ResponseEntity.notFound().build();
    }

    @DeleteMapping("/history/clear")
    public ResponseEntity<?> clearHistory(@AuthenticationPrincipal User user) {
        ragService.clearChatLogs(user);
        return ResponseEntity.ok(Map.of("message", "Chat history cleared successfully"));
    }
}


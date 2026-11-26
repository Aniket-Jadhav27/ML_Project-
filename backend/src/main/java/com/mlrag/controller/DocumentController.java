package com.mlrag.controller;

import com.mlrag.dto.ChunkDto;
import com.mlrag.entity.DocumentItem;
import com.mlrag.entity.User;
import com.mlrag.service.RagService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final RagService ragService;

    public DocumentController(RagService ragService) {
        this.ragService = ragService;
    }

    @PostMapping("/upload")
    public ResponseEntity<?> upload(
            @RequestParam("file") MultipartFile file,
            @AuthenticationPrincipal User user) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("message", "Uploaded file is empty"));
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null) {
            originalFilename = "uploaded_file";
        }

        try {
            DocumentItem doc = ragService.uploadAndIndex(originalFilename, file.getBytes(), user);
            return ResponseEntity.ok(doc);
        } catch (IOException e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("message", "File upload failed: " + e.getMessage()));
        }
    }

    @GetMapping("/list")
    public ResponseEntity<List<DocumentItem>> listDocuments(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(ragService.getDocuments(user));
    }

    @GetMapping("/chunks")
    public ResponseEntity<List<ChunkDto>> getChunks(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(ragService.getAllIndexedChunks(user));
    }

    @GetMapping(value = "/structure", produces = "application/json")
    public ResponseEntity<String> getStructure(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(ragService.getDocumentStructure(user));
    }

    @GetMapping(value = "/tables", produces = "application/json")
    public ResponseEntity<String> getTables(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(ragService.getDocumentTables(user));
    }
}

package com.mlrag.dto;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

public class ChatResponse {
    private String question;
    private String answer;
    private List<ChunkDto> chunks = new ArrayList<>();
    private LocalDateTime timestamp = LocalDateTime.now();

    public ChatResponse() {}

    public ChatResponse(String question, String answer, List<ChunkDto> chunks) {
        this.question = question;
        this.answer = answer;
        this.chunks = chunks != null ? chunks : new ArrayList<>();
        this.timestamp = LocalDateTime.now();
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public List<ChunkDto> getChunks() {
        return chunks;
    }

    public void setChunks(List<ChunkDto> chunks) {
        this.chunks = chunks;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }
}


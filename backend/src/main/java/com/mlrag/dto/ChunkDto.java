package com.mlrag.dto;

public class ChunkDto {
    private Object id;
    private Integer chunkId;
    private Integer page;
    private Integer startChar;
    private Integer endChar;
    private String source;
    private String text;
    private Double distance;
    private String chunkType;
    private Integer tableId;

    public ChunkDto() {}

    public ChunkDto(Object id, Integer chunkId, Integer page, Integer startChar, Integer endChar, String source, String text, Double distance) {
        this.id = id;
        this.chunkId = chunkId;
        this.page = page;
        this.startChar = startChar;
        this.endChar = endChar;
        this.source = source;
        this.text = text;
        this.distance = distance;
        this.chunkType = "body";
        this.tableId = 0;
    }

    public ChunkDto(Object id, Integer chunkId, Integer page, Integer startChar, Integer endChar, String source, String text, Double distance, String chunkType, Integer tableId) {
        this.id = id;
        this.chunkId = chunkId;
        this.page = page;
        this.startChar = startChar;
        this.endChar = endChar;
        this.source = source;
        this.text = text;
        this.distance = distance;
        this.chunkType = chunkType;
        this.tableId = tableId;
    }

    public Object getId() {
        return id != null ? id : chunkId;
    }

    public void setId(Object id) {
        this.id = id;
    }

    public Integer getChunkId() {
        return chunkId;
    }

    public void setChunkId(Integer chunkId) {
        this.chunkId = chunkId;
    }

    public Integer getPage() {
        return page;
    }

    public void setPage(Integer page) {
        this.page = page;
    }

    public Integer getStartChar() {
        return startChar;
    }

    public void setStartChar(Integer startChar) {
        this.startChar = startChar;
    }

    public Integer getEndChar() {
        return endChar;
    }

    public void setEndChar(Integer endChar) {
        this.endChar = endChar;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public Double getDistance() {
        return distance;
    }

    public void setDistance(Double distance) {
        this.distance = distance;
    }

    public String getChunkType() {
        return chunkType;
    }

    public void setChunkType(String chunkType) {
        this.chunkType = chunkType;
    }

    public Integer getTableId() {
        return tableId;
    }

    public void setTableId(Integer tableId) {
        this.tableId = tableId;
    }
}

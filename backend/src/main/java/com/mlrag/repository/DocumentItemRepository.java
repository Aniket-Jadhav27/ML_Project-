package com.mlrag.repository;

import com.mlrag.entity.DocumentItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentItemRepository extends JpaRepository<DocumentItem, Long> {
    List<DocumentItem> findAllByOrderByUploadedAtDesc();
    List<DocumentItem> findByUploadedByOrderByUploadedAtDesc(String uploadedBy);
}


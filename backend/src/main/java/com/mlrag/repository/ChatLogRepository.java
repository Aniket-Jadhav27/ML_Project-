package com.mlrag.repository;

import com.mlrag.entity.ChatLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatLogRepository extends JpaRepository<ChatLog, Long> {
    List<ChatLog> findAllByOrderByTimestampDesc();
    List<ChatLog> findByUserIdOrderByTimestampDesc(Long userId);
    List<ChatLog> findByUsernameOrderByTimestampDesc(String username);
}


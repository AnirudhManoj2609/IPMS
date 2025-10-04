package com.ipms.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.ipms.model.MessageEntity;

@Repository
public interface MessageRepository extends JpaRepository<MessageEntity, Long> {
    List<MessageEntity> findByReceiverIdAndDeliveredFalse(Long receiverId);
    List<MessageEntity> findByMovieIdOrderByTimestampAsc(Long movieId);
}

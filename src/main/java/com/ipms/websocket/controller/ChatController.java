package com.ipms.websocket.controller;

import java.nio.file.AccessDeniedException;
import java.security.Principal;
import java.util.Date;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.web.socket.WebSocketSession;

import com.ipms.dto.ChatDto;
import com.ipms.model.MessageEntity;
import com.ipms.repository.MessageRepository;
import com.ipms.service.UserMovieService;
import com.ipms.websocket.OnlineUserManager;

@Controller
public class ChatController {

    @Autowired
    private UserMovieService umService;

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private MessageRepository messageRepository;

    // ------------------- Broadcast messages -------------------
    @MessageMapping("/chat.sendMessage/{movieId}")
    public void sendMovieMessage(@DestinationVariable Long movieId, ChatDto chatMessage, Principal principal) throws Exception {
        Long userId = umService.getUserIdFromUsername(principal.getName());

        if (!umService.isUserInMovie(userId, movieId)) {
            throw new AccessDeniedException("You are not a collaborator on this movie!");
        }

        chatMessage.setMovieId(movieId);
        chatMessage.setUsername(principal.getName());
        chatMessage.setTimeStamp(new Date());

        // Broadcast to everyone in movie topic
        messagingTemplate.convertAndSend("/topic/movie/" + movieId, chatMessage);

        // Store message in DB
        MessageEntity entity = new MessageEntity();
        entity.setMovieId(movieId);
        entity.setSenderId(userId);
        entity.setReceiverId(null); // null for broadcast
        entity.setContent(chatMessage.getMessage());
        entity.setTimestamp(new Date());
        entity.setDelivered(true); // delivered immediately
        messageRepository.save(entity);
    }

    // ------------------- Personal messages -------------------
    @MessageMapping("/chat.sendPrivate/{movieId}/{toUserId}")
    public void sendPrivateMessage(@DestinationVariable Long movieId,
                                   @DestinationVariable Long toUserId,
                                   ChatDto chatMessage,
                                   Principal principal) throws Exception {

        Long fromUserId = umService.getUserIdFromUsername(principal.getName());

        if (!umService.isUserInMovie(fromUserId, movieId) ||
            !umService.isUserInMovie(toUserId, movieId)) {
            throw new AccessDeniedException("Either sender or receiver not in movie!");
        }

        chatMessage.setMovieId(movieId);
        chatMessage.setUsername(principal.getName());
        chatMessage.setUserId(fromUserId);
        chatMessage.setTimeStamp(new Date());

        String toUsername = umService.getUsernameFromId(toUserId);

        // Save message in DB first
        MessageEntity entity = new MessageEntity();
        entity.setMovieId(movieId);
        entity.setSenderId(fromUserId);
        entity.setReceiverId(toUserId);
        entity.setContent(chatMessage.getMessage());
        entity.setTimestamp(new Date());
        entity.setDelivered(false); // default to offline
        messageRepository.save(entity);

        // Send if user is online
        if (OnlineUserManager.isOnline(movieId, toUserId)) {
            messagingTemplate.convertAndSendToUser(toUsername, "/queue/private", chatMessage);
            entity.setDelivered(true);
            messageRepository.save(entity);
        }
    }

    // ------------------- User joins project -------------------
    @MessageMapping("/chat.addUser/{movieId}")
    public void addUser(@DestinationVariable Long movieId, Principal principal, WebSocketSession session) throws Exception {
        Long userId = umService.getUserIdFromUsername(principal.getName());

        // Track user as online
        OnlineUserManager.addUser(movieId, userId, session);

        ChatDto chatMessage = new ChatDto();
        chatMessage.setType(ChatDto.MessageType.JOIN);
        chatMessage.setTimeStamp(new Date());
        chatMessage.setMovieId(movieId);
        chatMessage.setUsername(principal.getName());
        chatMessage.setUserId(userId);

        // Broadcast new user to all in the movie
        messagingTemplate.convertAndSend("/topic/movie/" + movieId, chatMessage);

        // Deliver offline messages
        deliverPendingMessages(principal.getName(), userId);
    }

    // ------------------- Deliver offline messages -------------------
    private void deliverPendingMessages(String username, Long userId) {
        List<MessageEntity> pending = messageRepository.findByReceiverIdAndDeliveredFalse(userId);
        for (MessageEntity msg : pending) {
            ChatDto chat = new ChatDto();
            chat.setUsername(umService.getUsernameFromId(msg.getSenderId()));
            chat.setUserId(msg.getSenderId());
            chat.setMovieId(msg.getMovieId());
            chat.setMessage(msg.getContent());
            chat.setTimeStamp(msg.getTimestamp());

            messagingTemplate.convertAndSendToUser(username, "/queue/private", chat);
            msg.setDelivered(true);
            messageRepository.save(msg);
        }
    }
}

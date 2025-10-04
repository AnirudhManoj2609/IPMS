package com.ipms.websocket.controller;

import java.nio.file.AccessDeniedException;
import java.security.Principal;
import java.util.Date;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.*;

import com.ipms.dto.ChatDto;
import com.ipms.service.UserMovieService;

@Controller
public class ChatController {

    @Autowired
    private UserMovieService umService;
    

    @MessageMapping("/chat.sendMessage/{movieId}")
    @SendTo("/topic/movie/{movieId}")
    public ChatDto SendMessage(@DestinationVariable Long movieId,ChatDto chatMessage,Principal principal) throws Exception{
    
        Long userId = umService.getUserIdFromUsername(principal.getName());

        // Check if user is allowed to send message for this movie
        if (!umService.isUserInMovie(userId, movieId)) {
            throw new AccessDeniedException("You are not a collaborator on this movie!");
        }

        chatMessage.setMovieId(movieId);
        chatMessage.setTimeStamp(new Date());
        chatMessage.setUsername(principal.getName());
        return chatMessage;
    }

    @MessageMapping("/chat.addUser/{movieId}")
    @SendTo("/topic/movie/{movieId}")
    public ChatDto addUser(@DestinationVariable Long movieId,ChatDto chatMessage){
        chatMessage.setType(ChatDto.MessageType.JOIN);
        chatMessage.setTimeStamp(new Date());
        chatMessage.setMovieId(movieId);
        return chatMessage;
    }
}

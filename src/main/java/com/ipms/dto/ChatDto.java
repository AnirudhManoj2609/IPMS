package com.ipms.dto;

import java.util.Date;

import lombok.Data;

@Data
public class ChatDto {
    private String username;
    private String message;
    private Long movieId;
    private Long userId;
    private Date timeStamp;

    public enum MessageType{
        CHAT,
        JOIN,
        LEAVE
    }
    private MessageType type;
}

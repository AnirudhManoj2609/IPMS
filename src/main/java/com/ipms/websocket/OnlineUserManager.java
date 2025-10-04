package com.ipms.websocket;

import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import org.springframework.web.socket.WebSocketSession;

public class OnlineUserManager {

    // movieId -> (userId -> WebSocketSession)
    private static final Map<Long, Map<Long, WebSocketSession>> onlineUsers = new ConcurrentHashMap<>();

    public static void addUser(Long movieId, Long userId, WebSocketSession session) {
        onlineUsers.computeIfAbsent(movieId, k -> new ConcurrentHashMap<>()).put(userId, session);
    }

    public static void removeUser(Long movieId, Long userId) {
        if (onlineUsers.containsKey(movieId)) {
            onlineUsers.get(movieId).remove(userId);
        }
    }

    public static boolean isOnline(Long movieId, Long userId) {
        return onlineUsers.containsKey(movieId) && onlineUsers.get(movieId).containsKey(userId);
    }
}

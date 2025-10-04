package com.ipms.websocket.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * Configures the WebSocket connection and STOMP message broker.
 * This is the foundation for real-time, topic-based messaging.
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // 1. Broker: Defines the prefix for destinations the server pushes messages to.
        // Clients subscribe to topics like: /topic/movie/{movieId}
        config.enableSimpleBroker("/topic");
        
        // 2. Application Prefix: Defines the prefix for endpoints that controllers handle.
        // Clients send messages to: /app/chat.sendMessage
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // 1. Endpoint: Registers the primary connection endpoint for the WebSocket handshake.
        // Frontend will connect to: ws://localhost:8080/ws
        // 2. CORS: setAllowedOriginPatterns("*") is essential for frontend communication (like localhost:3000).
        // 3. SockJS: provides a fallback option for older browsers.
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*") 
                .withSockJS(); 
    }
}

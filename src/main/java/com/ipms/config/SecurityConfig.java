package com.ipms.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod; // Need this for OPTIONS method
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // 1. **CRITICAL CORS FIX: ENABLE CORS**
            // This tells Spring Security to use the configuration defined in your CorsConfig.java.
            .cors(Customizer.withDefaults()) 

            .csrf(csrf -> csrf.disable()) // Disable CSRF for state-less REST APIs

            .authorizeHttpRequests(auth -> auth
                // 2. **CRITICAL CORS FIX: PERMIT OPTIONS**
                // Browsers send an HTTP OPTIONS request as a preflight check for complex CORS requests (like POST with JSON).
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                
                // 3. PERMIT AUTHENTICATION ENDPOINTS
                // Allow unauthenticated access to login and registration paths.
                .requestMatchers("/api/auth/register", "/api/auth/login").permitAll()
                .requestMatchers("/virtual/ADHD").permitAll() // Keep this for your specific path

                // 4. **CRITICAL SECURITY FIX**
                // All other requests must be authenticated. Your original code said .permitAll(), which disabled security entirely.
                .anyRequest().authenticated()
            )
            .httpBasic(Customizer.withDefaults());

        return http.build();
    }
}

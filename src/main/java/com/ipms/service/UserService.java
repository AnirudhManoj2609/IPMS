package com.ipms.service;

import com.ipms.repository.*;
import com.ipms.dto.*;
import com.ipms.model.*;

import java.util.Optional;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
        this.passwordEncoder = new BCryptPasswordEncoder();
    }

    public User registerUser(UserDto userDto) {
        try{
            if (userRepository.existsByEmail(userDto.getEmail())) {
                throw new RuntimeException("Email already in use");
            }
            User user = new User();
            user.setPassword(passwordEncoder.encode(userDto.getPassword()));
            
            user.setUsername(userDto.getUsername());
            user.setEmail(userDto.getEmail());
            return userRepository.save(user);
        }
        catch(Exception e){
            throw e;
        }
    }
    public User loginUser(LoginDto loginDto){
        try{
            Optional<User> optUser = userRepository.findByEmail(loginDto.getEmail());
            if(optUser.isEmpty()){
                throw new RuntimeException("User not found: " + loginDto.getEmail());
            }
            User user = optUser.get();
            if(!passwordEncoder.matches(loginDto.getPassword(), user.getPassword())) {
                throw new RuntimeException("Invalid password");
            }
            return user;
        }
        catch(Exception e){
            throw new RuntimeException("Login Error: " + e.getMessage());
        }
    }

    public User getUser(Long userId){
        try{
            Optional<User> optUser = userRepository.findById(userId);
            if(optUser.isEmpty()){
                throw new RuntimeException("User not found!");
            }
            User user = optUser.get();
            return user;
        }
        catch(Exception e){
            throw new RuntimeException("User Error: " + e.getMessage());
        }
    }
}

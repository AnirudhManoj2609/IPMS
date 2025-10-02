package com.ipms.service;

import com.ipms.repository.*;
import com.ipms.dto.UserDto;
import com.ipms.model.*;

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
            if(userDto.getRole() == null){
                user.setRole("USER");
            }
            else{
                user.setRole(userDto.getRole());
            }
            user.setUsername(userDto.getUsername());
            user.setEmail(userDto.getEmail());
            return userRepository.save(user);
        }
        catch(Exception e){
            throw e;
        }
    }
}

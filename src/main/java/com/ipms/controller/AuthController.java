package com.ipms.controller;

import com.ipms.service.*;
import com.ipms.model.*;
import com.ipms.response.UserResponse;
import com.ipms.dto.*;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private final UserService userService;

    public AuthController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@RequestBody UserDto userDto) {
        try{
            User user = userService.registerUser(userDto);
            if(user != null){
                UserResponse userResponse = new UserResponse("User Registeration Successful!",user.getId());
                return new ResponseEntity<>(userResponse,HttpStatus.CREATED);
            }
            else{
                UserResponse userResponse = new UserResponse("Couldn't create User", null);
                return new ResponseEntity<>(userResponse, HttpStatus.NOT_IMPLEMENTED);
            }
        }
        catch(Exception e){
            UserResponse userResponse = new UserResponse("Error during user creation", null);
            return new ResponseEntity<>(userResponse,HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @PostMapping("/login")
    public String login(@RequestBody User user) {
        
        return "Login endpoint works!";
    }
}

package com.ipms.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;

import com.ipms.dto.MovieDto;
import com.ipms.model.*;
import com.ipms.response.UserResponse;
import com.ipms.service.*;

@Controller
@RequestMapping("/api/movie")
public class MovieController {
    
    private final MovieService mService;
    private final UserService uService;
    public MovieController(MovieService scriptService,UserService us) {
        mService = scriptService;
        uService = us;
    }

    @PostMapping("/add")
    public ResponseEntity<UserResponse> addMovie(@RequestBody MovieDto movieDto){
        try{
            Movie movie = mService.addMovie(movieDto.getTitle(),movieDto.getGenre());
            if(movie != null){
                mService.addUserToMovie(movie.getId(), movieDto.getUserId(),movieDto.getUserRole());
                UserResponse userResponse = new UserResponse("Script Added Successful!",movie.getId());
                return new ResponseEntity<>(userResponse,HttpStatus.CREATED);
            }
            else{
                UserResponse userResponse = new UserResponse("Couldn't add script", null);
                return new ResponseEntity<>(userResponse, HttpStatus.NOT_IMPLEMENTED);
            }
        }
        catch(Exception e){
            UserResponse userResponse = new UserResponse("Error during user creation", null);
            return new ResponseEntity<>(userResponse,HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}


package com.ipms.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import com.ipms.dto.ScriptDto;
import com.ipms.model.Scripts;
import com.ipms.response.UserResponse;
import com.ipms.service.ScriptService;

@Controller
@RequestMapping("/api/scripts")
public class ScriptController {
    
    private final ScriptService sService;

    public ScriptController(ScriptService scriptService) {
        sService = scriptService;
    }

    @PostMapping("/add")
    public ResponseEntity<UserResponse> addScript(@RequestBody ScriptDto scriptDto){
        try{
            Scripts script = sService.addScript(scriptDto.getMovieId(), scriptDto.getTitle(),scriptDto.getContent());
            if(script != null){
                UserResponse userResponse = new UserResponse("Script Added Successful!",script.getId());
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


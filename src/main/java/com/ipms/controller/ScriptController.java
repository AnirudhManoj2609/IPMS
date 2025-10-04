package com.ipms.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import com.ipms.dto.ScriptDto;
import com.ipms.model.Scripts;
import com.ipms.response.UserResponse;
import com.ipms.service.*;

@Controller
@RequestMapping("/api/scripts")
public class ScriptController {
    
    private final ScriptService sService;

    public ScriptController(ScriptService scriptService) {
        sService = scriptService;
    }

    @PostMapping(value = "/add", consumes = {"multipart/form-data"})
    public ResponseEntity<UserResponse> addScript(
            @RequestPart("scriptDto") ScriptDto scriptDto,
            @RequestPart(value = "pdfFile", required = false) MultipartFile pdfFile) {
        try {
            Scripts script = sService.addScript(
                scriptDto.getMovieId(),
                scriptDto.getTitle(),
                scriptDto.getContent(),
                pdfFile
            );

            if (script != null) {
                String pdfPath = script.getPdfLink();
                if(pdfPath != null && pdfFile != null && !pdfFile.isEmpty()){
                    sService.processBatchScriptAnalysis(script.getMovie().getId(), pdfPath);
                }
                UserResponse userResponse = new UserResponse("Script Added Successfully!", script.getId());
                return new ResponseEntity<>(userResponse, HttpStatus.CREATED);
            } else {
                UserResponse userResponse = new UserResponse("Couldn't add script", null);
                return new ResponseEntity<>(userResponse, HttpStatus.NOT_IMPLEMENTED);
            }
        } catch (Exception e) {
            UserResponse userResponse = new UserResponse("Error during script creation: " + e.getMessage(), null);
            return new ResponseEntity<>(userResponse, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}


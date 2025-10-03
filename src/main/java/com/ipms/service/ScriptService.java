package com.ipms.service;

import java.io.File;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.ipms.model.*;
import com.ipms.repository.MovieRepository;
import com.ipms.repository.ScriptRepository;

@Service
public class ScriptService{
    
    private final ScriptRepository sRepository;
    private final MovieRepository mRepository;

    public ScriptService(ScriptRepository sr,MovieRepository mr){
        sRepository = sr;
        mRepository = mr;
    }

    public Scripts addScript(Long movieId,String title,String content,MultipartFile pdfFile){
        try{
            Movie movie = mRepository.findById(movieId).orElseThrow(() -> new RuntimeException("Movie not found!"));
            
            Scripts script = new Scripts();
            script.setTitle(title);
            script.setMovie(movie);

            if(content != null && !content.isEmpty()){
                script.setScriptText(content);
            }
            if(pdfFile != null && !pdfFile.isEmpty()){
                String filePath = "/uploads/scripts/" + pdfFile.getOriginalFilename();
                pdfFile.transferTo(new File(filePath));
                script.setPdfLink(filePath); 
            }
            if(script.getScriptText() == null && script.getPdfLink() == null) {
                throw new IllegalArgumentException("Either content or PDF must be provided.");
            }

            return sRepository.save(script);
        }   
        catch(Exception e){
            throw new RuntimeException("Some error has occured!");
        }
    }

    public List<Scripts> getScriptsByMovie(Long movieId){
        return sRepository.findByMovieId(movieId);
    }
}

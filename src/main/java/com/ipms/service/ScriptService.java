package com.ipms.service;

import java.io.File;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.ipms.model.*;
import com.ipms.repository.MovieRepository;
import com.ipms.repository.ScriptRepository;

import jakarta.transaction.Transactional;

@Service
public class ScriptService{
    
    private final ScriptAnalysisClient analysisClient;
    private final ScriptRepository sRepository;
    private final MovieRepository mRepository;
    private final UserMovieService userMovieService; // Inject this

    

    public ScriptService(ScriptAnalysisClient SAC,ScriptRepository sr,MovieRepository mr,UserMovieService UMS){
        sRepository = sr;
        mRepository = mr;
        userMovieService = UMS; 
        analysisClient = SAC;
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

    @Transactional
    public void processBatchScriptAnalysis(Long movieId, String pdfPath) {
        System.out.println("Starting batch analysis for Movie ID: " + movieId);
        
        // 1. Get the combined analysis JSON from FastAPI
        String fullAnalysisResultJson = analysisClient.analyzeScriptPdf(pdfPath);
        
        if (fullAnalysisResultJson == null) {
            System.err.println("Batch analysis failed to retrieve results from FastAPI.");
            // Decide if you want to throw an exception here
            return;
        }
        
        userMovieService.updateAllMovieUsersWithAnalysis(movieId, fullAnalysisResultJson);
    }
}

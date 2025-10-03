package com.ipms.service;

import java.util.List;

import org.springframework.stereotype.Service;

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

    public Scripts addScript(Long movieId,String title,String content){
        try{
            Movie movie = mRepository.findById(movieId).orElseThrow(() -> new RuntimeException("Movie not found!"));
            
            Scripts script = new Scripts();
            script.setTitle(title);
            script.setScriptText(content);
            script.setMovie(movie);

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

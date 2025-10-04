package com.ipms.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ipms.model.*;
import com.ipms.repository.*; 
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List; // Needed for the batch process
import java.util.Optional;

@Service
public class UserMovieService {

    private final ObjectMapper objectMapper;
    private final UserMovieRepository userMovieRepository;
    private final UserRepository userRepository;
    private final MovieRepository movieRepository;

    public UserMovieService(
            UserMovieRepository userMovieRepository,
            UserRepository userRepository,
            MovieRepository movieRepository) {
        // ObjectMapper is used to parse the large JSON string
        this.objectMapper = new ObjectMapper(); 
        this.userMovieRepository = userMovieRepository;
        this.userRepository = userRepository;
        this.movieRepository = movieRepository;
    }

    /*
     * NOTE: The previous 'saveRoleAnalysis' method is removed/replaced.
     * The logic below implements the correct batch update for all users assigned to the movie.
     */

    @Transactional
    public void updateAllMovieUsersWithAnalysis(Long movieId, String fullAnalysisResultJson) {
        System.out.println("Starting batch update for Movie ID: " + movieId);
        
        try {
            // 1. Get all UserMovie entries for the given Movie ID.
            //    (Requires a method in UserMovieRepository, e.g., 'findByMovie_Id')
            List<UserMovie> userMovies = userMovieRepository.findByMovieId(movieId);
            
            // 2. Parse the full JSON result once outside the loop for efficiency.
            JsonNode rootNode = objectMapper.readTree(fullAnalysisResultJson);

            // 3. Loop through every user assigned to this movie.
            for (UserMovie userMovie : userMovies) {
                String userRole = userMovie.getRole(); 

                // Convert the user role (e.g., "Director") to the JSON key (e.g., "director_analysis")
                String jsonKey = userRole.toLowerCase().replace(" ", "_") + "_analysis";
                
                // 4. Extract the specific role's analysis from the parsed JSON.
                JsonNode roleAnalysisNode = rootNode.get(jsonKey);

                if (roleAnalysisNode != null && !roleAnalysisNode.isNull()) {
                    // Convert the role-specific node back into a compact JSON string
                    String roleParametersJson = roleAnalysisNode.toString();
                    
                    userMovie.setParameters(roleParametersJson);
                    
                    userMovieRepository.save(userMovie);
                    
                    System.out.println("Updated analysis for Role: " + userRole + " for User: " + userMovie.getUser().getId());
                } else {
                    System.err.println("Skipping update: Analysis data not found for role: " + userRole);
                }
            }
        } catch (Exception e) {
            System.err.println("Fatal error during batch analysis update for Movie ID " + movieId + ": " + e.getMessage());
            // Rollback the transaction on failure
            throw new RuntimeException("Batch analysis failed to process or save parameters.", e);
        }
    }

    public Long getUserIdFromUsername(String username) throws Exception {
        return userRepository.findByUsername(username)
                       .orElseThrow(() -> new Exception("User not found"))
                       .getId();
    }

    // Check if a user is a collaborator on a movie
    public boolean isUserInMovie(Long userId, Long movieId) {
        return userMovieRepository.existsByUserIdAndMovieId(userId, movieId);
    }

    public String getUsernameFromId(Long userId){
        Optional<User> um =  userRepository.findById(userId);
        if(!um.isEmpty()){
            User UM = um.get();
            return UM.getUsername();
        }
        else{
            throw new RuntimeException("User not found!");
        }
    }

}
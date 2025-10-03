package com.ipms.service;

import java.util.Optional;

import org.springframework.stereotype.Service;
import com.ipms.model.*;
import com.ipms.repository.*;

import jakarta.transaction.Transactional;

@Service
public class MovieService{
    
    private final UserMovieRepository umRepository;
    private final MovieRepository movieRepository;
    private final UserRepository userRepository;
    
    public MovieService(UserMovieRepository umr,MovieRepository mr,UserRepository ur){
        umRepository = umr;
        movieRepository = mr;
        userRepository = ur;
    }

    public Movie addMovie(String title,String genre){
        try{
            Movie movie = new Movie();
            movie.setTitle(title);
            movie.setGenre(genre);
            return movieRepository.save(movie);
        }   
        catch(Exception e){
            throw new RuntimeException("Some error occured!");
        }
    }

    @Transactional
    public UserMovie addUserToMovie(Long movieId,Long userId,String role){
        try{
            Optional<Movie> optMovie = movieRepository.findById(movieId);
            Optional<User> optUser = userRepository.findById(userId);
            if(optMovie.isEmpty()){
                throw new RuntimeException("Movie does not exist!");
            }
            Movie movie = optMovie.get();
            if(optUser.isEmpty()){
                throw new RuntimeException("User does not exist!");
            }
            User user = optUser.get();
            boolean alreadyAdded = umRepository.existsByUserAndMovie(user,movie);
            if(alreadyAdded){
                throw new RuntimeException("User already exists!");
            }

            UserMovie userMovie = new UserMovie();
            userMovie.setUser(user);
            userMovie.setMovie(movie);
            userMovie.setRole(role);
            userMovie.setParameters("{}");

            return umRepository.save(userMovie);
        }
        catch(Exception e){
            throw new RuntimeException("Some error occured!");
        }
    }
}

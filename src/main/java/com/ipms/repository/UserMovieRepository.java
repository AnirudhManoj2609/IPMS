package com.ipms.repository;

import com.ipms.model.*;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserMovieRepository extends JpaRepository<UserMovie,Long>{
    boolean existsByUserAndMovie(User user,Movie movie);
    List<UserMovie> findByMovieId(Long movieId);
}

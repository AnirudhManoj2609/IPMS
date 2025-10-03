package com.ipms.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ipms.model.Movie;

public interface MovieRepository extends JpaRepository<Movie,Long>{
    
}

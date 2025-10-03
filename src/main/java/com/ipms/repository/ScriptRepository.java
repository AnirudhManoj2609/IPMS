package com.ipms.repository;

import com.ipms.model.*;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ScriptRepository extends JpaRepository<Scripts,Long>{
    List<Scripts> findByMovieId(Long movieId);
}

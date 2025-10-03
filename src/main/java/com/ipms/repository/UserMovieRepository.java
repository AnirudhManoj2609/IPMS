package com.ipms.repository;

import com.ipms.model.*;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserMovieRepository extends JpaRepository<UserMovie,Long>{
    boolean existsByUserAndMovie(User user,Movie movie);
}

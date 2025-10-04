package com.ipms.repository;

import com.ipms.model.*;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    Optional<User> findByUsername(String usernmae);
    boolean existsByEmail(String email);
}

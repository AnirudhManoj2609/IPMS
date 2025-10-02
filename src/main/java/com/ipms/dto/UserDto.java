package com.ipms.dto;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Data
public class UserDto{
  
    
    private String username;

    private String email;

    private String password;

    private String role;
}

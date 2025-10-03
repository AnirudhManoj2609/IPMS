package com.ipms.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "user_movies")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserMovie{
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne
    @JoinColumn(name = "user_id")
    private User user;

    @ManyToOne
    @JoinColumn(name = "movie_id")
    private Movie movie;

    private String role;

    @Column(columnDefinition = "jsonb")
    private String parameters;
}

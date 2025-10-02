package com.ipms.response;

import lombok.*;

@Getter
@Setter
@AllArgsConstructor
public class UserResponse{
    String message;
    Object id;
    public UserResponse(String m,Long i){
        this.message = m;
        this.id = i;
    }
}

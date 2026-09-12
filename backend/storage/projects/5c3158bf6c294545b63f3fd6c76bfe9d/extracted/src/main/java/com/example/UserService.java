package com.example;

public class UserService {
    public User getUser(String id) {
        return new User(id);
    }

    public void saveUser(User user) {
        System.out.println('Saved ' + user.getName());
    }
}

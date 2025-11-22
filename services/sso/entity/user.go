package entity

import "time"

type (
	User struct {
		ID        string    `json:"id"`
		Name      string    `json:"first_name"`
		Surname   *string   `json:"last_name"`
		Email     string    `json:"email"`
		Password  string    `json:"-"`
		CreatedAt time.Time `json:"created_at"`
		UpdatedAt time.Time `json:"updated_at"`
	}
)

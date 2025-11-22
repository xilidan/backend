package entity

type (
	GetUserRequest struct {
		ID string
	}

	GetUserResponse struct {
		User *User
	}
)

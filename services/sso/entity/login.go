package entity

type (
	LoginRequest struct {
		Email    string
		Password string
	}

	LoginResponse struct {
		Token string
	}
)

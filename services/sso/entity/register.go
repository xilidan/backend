package entity

type (
	RegitserRequest struct {
		Email           string
		Name            string
		Surname         *string
		Password        string
		PasswordConfirm string
	}

	RegisterResponse struct {
		Token string
	}
)

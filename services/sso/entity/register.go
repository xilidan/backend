package entity

type (
	RegitserRequest struct {
		Email           string
		Name            string
		Surname         *string
		PositionID      int
		Password        string
		PasswordConfirm string
	}

	RegisterResponse struct {
		Token string
	}
)

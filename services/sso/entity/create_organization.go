package entity

type (
	CreateOrganizationReq struct {
		Name      string
		Users     []*User
		Positions []*Position
		UserID    string
	}

	CreateOrganizationResp struct {
		Organization *Organization
	}
)

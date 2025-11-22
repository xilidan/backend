package entity

type (
	CreateOrganizationReq struct {
		Name      string
		Users     []User
		Positions []Position
	}

	CreateOrganizationResp struct {
		Organization Organization
	}
)

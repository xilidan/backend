package entity

type (
	UpdateOrganizationReq struct {
		ID        string
		Name      string
		Users     []User
		Positions []Position
	}

	UpdateOrgnaizationResp struct {
		Organization Organization
	}
)

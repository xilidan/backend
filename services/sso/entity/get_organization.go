package entity

type (
	GetOrganizationReq struct {
		UserID string
	}

	GetOrganizationResp struct {
		Organization *Organization
	}
)

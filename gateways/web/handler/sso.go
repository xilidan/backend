package handler

import (
	"fmt"
	"net/http"

	"github.com/xilidan/backend/pkg/json"
	"github.com/xilidan/backend/pkg/jwt"
	pb "github.com/xilidan/backend/specs/proto/specs/proto/sso"
)

func (h *handler) LoginHandler(w http.ResponseWriter, r *http.Request) {
	req := &pb.LoginReq{}
	json.ParseProtoJSON(r, req)

	res, err := h.SsoClient.Login(r.Context(), req)
	if err != nil {
		json.WriteError(w, http.StatusInternalServerError, fmt.Errorf("Неправильный пароль или email"))
		return
	}

	json.WriteProtoJSON(w, http.StatusOK, res)
}

func (h *handler) RegisterHandler(w http.ResponseWriter, r *http.Request) {
	req := &pb.RegisterReq{}
	json.ParseProtoJSON(r, req)

	res, err := h.SsoClient.Register(r.Context(), req)
	if err != nil {
		json.WriteError(w, http.StatusInternalServerError, err)
		return
	}

	json.WriteProtoJSON(w, http.StatusOK, res)
}

func (h *handler) GetUserHandler(w http.ResponseWriter, r *http.Request) {
	req := &pb.GetUserReq{}

	token, err := jwt.ParseTokenFromHeader(r)
	if err != nil {
		json.WriteError(w, http.StatusForbidden, fmt.Errorf("access denied"))
	}

	userID, err := jwt.ParseUserID(r.Context(), token, h.cfg.JWTSecret)
	if err != nil {
		json.WriteError(w, http.StatusForbidden, fmt.Errorf("access denied"))
	}

	req.UserId = userID

	res, err := h.SsoClient.GetUser(r.Context(), req)
	if err != nil {
		json.WriteError(w, http.StatusInternalServerError, err)
		return
	}

	json.WriteProtoJSON(w, http.StatusOK, res)
}

func (h *handler) CreateOrganizationHandler(w http.ResponseWriter, r *http.Request) {
	
}

func (h *handler) GetOrganizationHandler(w http.ResponseWriter, r *http.Request) {
	req := &pb.GetOrganizationReq{}

	token, err := jwt.ParseTokenFromHeader(r)
	if err != nil {
		json.WriteError(w, http.StatusForbidden, fmt.Errorf("access denied"))
	}

	userID, err := jwt.ParseUserID(r.Context(), token, h.cfg.JWTSecret)
	if err != nil {
		json.WriteError(w, http.StatusForbidden, fmt.Errorf("access denied"))
	}

	req.Id = userID

	res, err := h.SsoClient.GetOrganization(r.Context(), req)
	if err != nil {
		json.WriteError(w, http.StatusInternalServerError, err)
		return
	}

	json.WriteProtoJSON(w, http.StatusOK, res)
}

func (h *handler) UpdateOrganizationHandler(w http.ResponseWriter, r *http.Request) {
	json.WriteError(w, http.StatusInternalServerError, fmt.Errorf("not implemented"))
}

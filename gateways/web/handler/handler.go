package handler

import "net/http"

type handler struct {}

type Handler interface {
	GenerateHandler(w http.ResponseWriter, r *http.Request)
}

func NewHandler() Handler {
	return &handler{}
}

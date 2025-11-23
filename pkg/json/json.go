package json

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
)

func ParseJSON(r *http.Request, model any) error {
	if r.Body == nil {
		return fmt.Errorf("Missing request body")
	}

	return json.NewDecoder(r.Body).Decode(model)
}

func ParseProtoJSON(r *http.Request, msg proto.Message) error {
	if r.Body == nil {
		return fmt.Errorf("missing request body")
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		return fmt.Errorf("failed to read request body: %w", err)
	}

	unmarshaler := protojson.UnmarshalOptions{
		DiscardUnknown: true,
		AllowPartial:   false,
	}

	if err := unmarshaler.Unmarshal(body, msg); err != nil {
		return fmt.Errorf("failed to parse protobuf JSON: %w", err)
	}

	return nil
}

func WriteJSON(w http.ResponseWriter, status int, v any) error {
	w.Header().Add("Content-Type", "application/json")
	w.WriteHeader(status)

	return json.NewEncoder(w).Encode(v)
}

func WriteProtoJSON(w http.ResponseWriter, status int, msg proto.Message) error {
	marshaler := protojson.MarshalOptions{
		EmitUnpopulated: false, // Don't include zero values
		UseProtoNames:   false, // Use JSON names (camelCase)
		UseEnumNumbers:  false, // Use enum names instead of numbers
	}

	data, err := marshaler.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to marshal protobuf to JSON: %w", err)
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, err = w.Write(data)
	return err
}

func WriteError(w http.ResponseWriter, status int, err error) {
	WriteJSON(w, status, map[string]string{"error": err.Error()})
}

package asr

import (
	"fmt"

	config "github.com/xilidan/backend/config/meet"
	pb "github.com/xilidan/backend/specs/proto/asr"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type Client struct {
	conn *grpc.ClientConn
	pb.AsrServiceClient
}

func New(cfg *config.ServiceConfig) (*Client, error) {
	address := fmt.Sprintf("%s:%d", cfg.Url, cfg.Port)

	conn, err := grpc.NewClient(
		address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create grpc connection: %w", err)
	}

	return &Client{
		conn:             conn,
		AsrServiceClient: pb.NewAsrServiceClient(conn),
	}, nil
}

func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

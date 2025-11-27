package sso

import (
	"fmt"
	config "github.com/xilidan/backend/config/web"
	pb "github.com/xilidan/backend/specs/proto/sso"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type Client struct {
	conn *grpc.ClientConn
	pb.SsoServiceClient
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
		SsoServiceClient: pb.NewSsoServiceClient(conn),
	}, nil
}

func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

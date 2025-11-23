package config

import (
	"github.com/ilyakaznacheev/cleanenv"
)

type Config struct {
	JWTSecret string `env:"JWT_SECRET"`
	Database  DatabaseConfig
	Port      int `env:"PORT"`
}

type DatabaseConfig struct {
	User     string `env:"DB_USER"`
	Password string `env:"DB_PASSWORD"`
	Host     string `env:"DB_HOST"`
	Name     string `env:"DB_NAME"`
	Port     int    `env:"DB_PORT"`
	SSLMode  string `env:"DB_SSLMODE"`
}

func MustLoad() *Config {
	var cfg Config
	if err := cleanenv.ReadEnv(&cfg); err != nil {
		panic("failed to read environment variables: " + err.Error())
	}

	return &cfg
}

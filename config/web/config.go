package config

import "github.com/ilyakaznacheev/cleanenv"

type Config struct {
	SsoService ServiceConfig
	JWTSecret  string `env:"JWT_SECRET"`
}

type ServiceConfig struct {
	Port int    `env:"SSO_PORT"`
	Url  string `env:"SSO_URL"`
}

func MustLoad() *Config {
	var cfg Config
	if err := cleanenv.ReadEnv(&cfg); err != nil {
		panic("failed to read environment variables: " + err.Error())
	}
	return &cfg
}

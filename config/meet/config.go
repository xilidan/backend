package config

import "github.com/ilyakaznacheev/cleanenv"

type Config struct {
	Port            int           `env:"PORT"`
	FirefliesAPIKey string        `env:"FIREFLIES_API_KEY"`
	ScrumService    ServiceConfig `envPrefix:"SCRUM_"`
}

type ServiceConfig struct {
	Port int    `env:"PORT"`
	Url  string `env:"URL"`
}

func MustLoad() *Config {
	var cfg Config
	if err := cleanenv.ReadEnv(&cfg); err != nil {
		panic("failed to read environment variables: " + err.Error())
	}
	return &cfg
}

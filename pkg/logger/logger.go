package logger

import (
	"context"
	"io"
	"log/slog"
	"os"
)

type ctxKey string

const loggerKey ctxKey = "logger"

type Config struct {
	Level      slog.Level
	Output     io.Writer
	AddSource  bool
	JSONFormat bool
}

func New(cfg Config) *slog.Logger {
	if cfg.Output == nil {
		cfg.Output = os.Stdout
	}

	opts := &slog.HandlerOptions{
		Level:     cfg.Level,
		AddSource: cfg.AddSource,
	}

	var handler slog.Handler
	if cfg.JSONFormat {
		handler = slog.NewJSONHandler(cfg.Output, opts)
	} else {
		handler = slog.NewTextHandler(cfg.Output, opts)
	}

	return slog.New(handler)
}

func Default() *slog.Logger {
	return New(Config{
		Level:      slog.LevelInfo,
		Output:     os.Stdout,
		AddSource:  true,
		JSONFormat: false,
	})
}

func JSON() *slog.Logger {
	return New(Config{
		Level:      slog.LevelInfo,
		Output:     os.Stdout,
		AddSource:  true,
		JSONFormat: true,
	})
}

func WithContext(ctx context.Context, l *slog.Logger) context.Context {
	return context.WithValue(ctx, loggerKey, l)
}

func FromContext(ctx context.Context) *slog.Logger {
	if ctx == nil {
		return slog.Default()
	}
	if l, ok := ctx.Value(loggerKey).(*slog.Logger); ok {
		return l
	}
	return slog.Default()
}

func WithAttrs(l *slog.Logger, attrs ...slog.Attr) *slog.Logger {
	return l.With(attrsToAny(attrs)...)
}

func WithFields(l *slog.Logger, fields map[string]any) *slog.Logger {
	args := make([]any, 0, len(fields)*2)
	for k, v := range fields {
		args = append(args, k, v)
	}
	return l.With(args...)
}

func WithField(l *slog.Logger, key string, value any) *slog.Logger {
	return l.With(key, value)
}

func attrsToAny(attrs []slog.Attr) []any {
	args := make([]any, len(attrs))
	for i, attr := range attrs {
		args[i] = attr
	}
	return args
}

func Debug(ctx context.Context, msg string, args ...any) {
	FromContext(ctx).DebugContext(ctx, msg, args...)
}

func Info(ctx context.Context, msg string, args ...any) {
	FromContext(ctx).InfoContext(ctx, msg, args...)
}

func Warn(ctx context.Context, msg string, args ...any) {
	FromContext(ctx).WarnContext(ctx, msg, args...)
}

func Error(ctx context.Context, msg string, args ...any) {
	FromContext(ctx).ErrorContext(ctx, msg, args...)
}

func ErrorErr(ctx context.Context, msg string, err error, args ...any) {
	args = append(args, "error", err)
	FromContext(ctx).ErrorContext(ctx, msg, args...)
}

func With(ctx context.Context, args ...any) *slog.Logger {
	return FromContext(ctx).With(args...)
}

func SetDefault(l *slog.Logger) {
	slog.SetDefault(l)
}

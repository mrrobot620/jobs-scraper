# Define the Go binary name
BINARY=job_scraper

# Run the Go application
run:
	time ./${BINARY}

runp:
	time python3 main.py

# Build the Go binary
build:
	go build -o $(BINARY) main.go

# Format the Go code
fmt:
	go fmt ./...

# Run static analysis
lint:
	go vet ./...

# Clean up compiled binary
clean:
	rm -rf banking-finance food-factory healthcare hospitality it-engineering student

# Run tests (if you have tests)
test:
	go test ./...

# Run all checks (format, lint, test)
check: fmt lint test



# Default target (runs the app)
default: run


# To Do Recommendations App

This project is a scalable FastAPI application that serves an endpoint to recommend three things to do in a given country during a specific season by consulting the GROQ API. The application integrates a distributed component for background processing to handle the GROQ API calls asynchronously, stores the results in MongoDB, and signals completion. Docker Compose is used to manage the application components.

## Features

- FastAPI backend to handle recommendation requests
- Asynchronous processing of recommendations using Kafka
- MongoDB for storing recommendations
- Simple Bootstrap front-end for user interaction

## Setup

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ installed
- pipenv installed

### Initial Setup

1. Clone the repository:

```bash
git clone https://github.com/AleksSwan/aipiping.git
cd aipiping
```

2. Create a virtual environment and activate it:

```bash
pipenv sync
pipenv shell
```

3. Set up environment variables for the GROQ API key and other secrets (https://wow.groq.com/why-groq/, you can get api key after registration for free). Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
```

### Running the Application

1. Start the services using Docker Compose:

```bash
make run
```

2. Open your browser and navigate to `http://localhost:8000` to access the front-end.

## API Endpoints

### Request Recommendations

- **Endpoint:** `POST /recommendations`
- **Parameters:**
  - `country` (string): The country for which the recommendations are to be fetched.
  - `season` (string): The season in which the recommendations are desired (spring, summer, autumn, winter).
- **Response:**
  - `uid` (string): The unique identifier for the request.

### Check Recommendation Status

- **Endpoint:** `GET /recommendations/{uid}/status`
- **Parameters:**
  - `uid` (string): The unique identifier for the recommendation request.
- **Response:**
  - If the status is "pending":
    ```json
    {
      "uid": "1234567890abcdef",
      "status": "pending",
      "message": "The recommendations are not yet available. Please try again later."
    }
    ```
  - If the status is "completed":
    ```json
    {
      "uid": "1234567890abcdef",
      "status": "completed",
      "message": "No additional information available."
    }
    ```
  - If the UID is not found:
    ```json
    {
      "error": "UID not found",
      "message": "The provided UID does not exist. Please check the UID and try again."
    }
    ```

### Get Recommendation

- **Endpoint:** `GET /recommendations/{uid}`
- **Parameters:**
  - `uid` (string): The unique identifier for the recommendation request.
- **Response:**
  - If the status is "completed":
    ```json
    {
      "uid": "1234567890abcdef",
      "country": "Canada",
      "season": "winter",
      "recommendations": [
        "Go skiing in Whistler.",
        "Experience the Northern Lights in Yukon.",
        "Visit the Quebec Winter Carnival."
      ],
      "status": "completed"
    }
    ```
  - If the UID not found or status is not "completed":
    ```json
    {
      "error": "UID not found",
      "message": "The provided UID does not exist. Please check the UID and try again."
    }
    ```

## Front-end

A simple Bootstrap front-end is provided for user interaction. Users can enter a country and season, and request recommendations. The status and results will be displayed on the same page.

### Running the Front-end

To start the front-end:

1. Ensure you have Docker and Docker Compose installed.
2. Navigate to the root directory of the project.
3. Run the following command to start all services, including the front-end server:

```bash
make run
```

4. Open your browser and navigate to `http://localhost:8000` to access the front-end.

## Front-end Usage

1. Enter the country and select a season.
2. Click the "Get Recommendations" button.
3. The status of the request will be displayed, and the recommendations will be shown once they are available.

## Error Handling

The front-end handles various error states, such as invalid input or server errors, and provides feedback to the user.

## Logs

To view logs of specific services:

```bash
docker-compose logs backend worker
```

To suppress logs in Docker Compose:

```bash
docker-compose up -d
```

## Contribution

Feel free to fork this repository and contribute by submitting a pull request.

## License

This project is licensed under the MIT License.

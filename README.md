Steps to setup:<br/>
•	Install erlang<br/>
•	Set environment variables<br/>
•	Have an installation of python<br/>
•	Install RabbitMQ:<br/>
...run it using rabbitmq-server.bat<br/>
...to have a url to monitor use rabbitmq-plugins enable rabbitmq_management<br/>
...access using this url http://localhost:15672<br/>
•	Install python package pika<br/>
•	pip install feedparser requests beautifulsoup4<br/>
•	pip install openai python-dotenv<br/>
•	ensure that you have a .env file in the project folder with the OpenAI key set "OPENAI_API_KEY=your_OpenAI_key"<br/>
import json
import pika


def transaction_producer(transaction):
    '''
        - create a producer connection and connects to rabbitmq instance
        - creates a channel
    '''
    transaction = json.dumps(transaction)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost'))

    channel = connection.channel()

    channel.queue_declare(queue='transactions', durable=True)

    # publish a transaction to transactions exchange
    channel.basic_publish(exchange='',
                          routing_key='transactions',
                          body=transaction,
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))

    print(f'Transaction - {transaction} sent')

    connection.close()

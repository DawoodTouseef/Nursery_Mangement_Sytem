-- Create the database
CREATE DATABASE IF NOT EXISTS plants;

-- Use the database
USE plants;

-- Table for storing information about products (plants)
CREATE TABLE IF NOT EXISTS Product (
  p_id INT AUTO_INCREMENT PRIMARY KEY,
  p_name VARCHAR(100) NOT NULL,
  stock_available INT NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  description TEXT,
  supplier_id INT,
  image_url VARCHAR(255),
  FOREIGN KEY (supplier_id) REFERENCES Supplier(s_id) ON DELETE CASCADE
);

-- Table for storing information about suppliers
CREATE TABLE IF NOT EXISTS Supplier (
  s_id INT AUTO_INCREMENT PRIMARY KEY,
  company_name VARCHAR(100) NOT NULL,
  s_email VARCHAR(100) NOT NULL,
  password_hash TEXT NOT NULL,
  s_contact VARCHAR(20),
  s_address VARCHAR(255)
);

-- Table for storing information about users (customers)
CREATE TABLE IF NOT EXISTS Users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  user_email VARCHAR(100) NOT NULL,
  password_hash TEXT NOT NULL
);

-- Table for storing information about orders
CREATE TABLE IF NOT EXISTS Orders (
  order_id INT AUTO_INCREMENT PRIMARY KEY,
  reference VARCHAR(100),
  user_id INT,
  order_date DATE,
  delivery_date DATE,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  country VARCHAR(50),
  state VARCHAR(50),
  city VARCHAR(50),
  user_contact VARCHAR(20),
  user_address VARCHAR(255),
  status VARCHAR(50),
  total_amt DECIMAL(10, 2),
  payment_type VARCHAR(20),
  FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Table for storing information about items in each order
CREATE TABLE IF NOT EXISTS Order_Item (
  order_item_id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT,
  product_id INT,
  quantity INT,
  price DECIMAL(10, 2),
  FOREIGN KEY (order_id) REFERENCES Orders(order_id)ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES Product(p_id) ON DELETE CASCADE
);

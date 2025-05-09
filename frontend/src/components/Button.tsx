import React from 'react';
import styles from '../styles/Dashboard.module.css';
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'outline' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  'aria-label'?: string;
}

const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  type = 'button',
  'aria-label': ariaLabel,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all focus:outline-none';
  
  const variantStyles = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 border border-transparent',
    outline: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 border border-transparent',
  };
  
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs rounded',
    md: 'px-4 py-2 text-sm rounded',
    lg: 'px-6 py-3 text-base rounded-md',
  };
  
  const disabledStyles = disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';
  
  const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${disabledStyles} ${styles.button} ${className}`;
  
  return (
    <button
      type={type}
      className={combinedClassName}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button; 
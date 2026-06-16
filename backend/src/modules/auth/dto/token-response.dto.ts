export class TokenResponseDto {
  access_token: string;
  user: {
    user_id: string;
    username: string;
    email: string;
    role: string;
    full_name?: string;
  };
}